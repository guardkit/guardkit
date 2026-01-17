---
id: TASK-FB-FIX-018
title: Default documentation level to minimal, lift only on explicit flag
status: completed
created: 2026-01-13T19:30:00Z
updated: 2026-01-13T21:15:00Z
completed: 2026-01-13T21:15:00Z
priority: high
tags:
  - feature-build
  - documentation
  - performance
  - design-phase
complexity: 4
parent_review: TASK-REV-FE8A
implementation_mode: task-work
estimated_minutes: 90
actual_minutes: 45
dependencies:
  - TASK-FB-FIX-015
test_results:
  status: passed
  coverage: 100
  last_run: 2026-01-13T21:00:00Z
  tests_passed: 21
  tests_failed: 0
architectural_review:
  score: 82
  status: approved_with_recommendations
code_review:
  score: 9.5
  status: approved
completed_location: tasks/completed/TASK-FB-FIX-018/
organized_files:
  - TASK-FB-FIX-018.md
  - review-report.md
---

# Default Documentation Level to Minimal

## Summary

**Objective**: Change default documentation level from complexity-based auto-selection to always `minimal`, with explicit flag override support.

**Result**: ✅ Successfully implemented

## Problem Statement

The design phase (`/task-work --design-only`) was taking **89 minutes** for a **complexity 3/10 task** due to excessive documentation generation.

- Task complexity: 3/10
- Documentation level selected: STANDARD (bug - should be MINIMAL per spec)
- Actual output: 9+ files, 3,650+ lines (comprehensive-level)
- Expected output: 2 files, ~500-600 lines (minimal-level)

## Solution Implemented

Changed the default from complexity-based selection to **always minimal**, with explicit flag override support.

### Changes Made

1. **installer/core/commands/task-work.md** (8 locations):
   - Updated auto-selection documentation to show minimal as default
   - Changed Priority 4 logic from complexity-based to always `minimal`
   - Added file count constraints to all 4 DOCUMENTATION BEHAVIOR sections

2. **tests/unit/test_documentation_level_defaults.py** (new file):
   - 21 tests covering all acceptance criteria
   - Tests for default behavior, flag overrides, force triggers, hierarchy

### Behavioral Changes

| Scenario | Before | After |
|----------|--------|-------|
| Complexity 1-3, no flag | `minimal` | `minimal` (unchanged) |
| Complexity 4+, no flag | `standard` | `minimal` (CHANGED) |
| `--docs=standard` flag | `standard` | `standard` (unchanged) |
| Security keywords | `comprehensive` | `comprehensive` (unchanged) |

## Acceptance Criteria

- [x] Default documentation level is `minimal` regardless of complexity
- [x] `--docs=standard` flag still works to lift documentation level
- [x] `--docs=comprehensive` flag still works for full documentation
- [x] Only 2 core files generated in minimal mode (constraints added)
- [x] Agent prompts include explicit file count constraint for minimal mode
- [x] Unit tests verify new default behavior (21 tests, 100% pass)

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Design phase duration | 89 min | ~15-20 min |
| Files generated (minimal) | 9+ | 2 |
| Lines generated (minimal) | 3,650+ | ~500-600 |
| Default behavior | Complexity-based | Always minimal |

## Quality Gates

| Gate | Result |
|------|--------|
| Tests Pass | ✅ 21/21 (100%) |
| Architectural Review | ✅ 82/100 |
| Code Review | ✅ 9.5/10 |

## Notes

This change aligns with user feedback: "I rarely read the implementation plans as I've gained trust in the guardkit system." The quality gates (architectural review, tests, code review) provide the real value, not verbose documentation.

Users who need detailed documentation can explicitly request it with `--docs=comprehensive`.
