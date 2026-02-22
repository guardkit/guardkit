# Feature: Feature-Spec Review Fixes

**Feature ID:** FEAT-FSRF
**Parent Review:** TASK-REV-FCA5
**Created:** 2026-02-22
**Source:** `docs/reviews/feature-spec/TASK-REV-FCA5-review-report.md`

## Overview

Implementation tasks generated from the TASK-REV-FCA5 review of the FEAT-1253 feature-spec implementation. These address findings and recommendations from the architectural review.

## Tasks

| Task | Name | Priority | Complexity | Wave | Mode |
|------|------|----------|-----------|------|------|
| TASK-FSRF-001 | Commit FalkorDB workaround fix to branch | High | 1 | 1 | direct |
| TASK-FSRF-002 | Fix write_outputs stack passthrough | Low | 2 | 1 | task-work |
| TASK-FSRF-003 | Update CLAUDE.md with /feature-spec entry | Medium | 1 | 1 | direct |
| TASK-FSRF-004 | Add scan_codebase result to FeatureSpecResult | Low | 2 | 2 | task-work |
| TASK-FSRF-005 | Extend _read_input_files extension support | Low | 2 | 2 | task-work |
| TASK-FSRF-006 | Update feature-spec-command README task statuses | Low | 1 | 1 | direct |

## Execution Strategy

### Wave 1 (Parallel, 4 tasks)

All can run concurrently — no dependencies between them:
- TASK-FSRF-001: git operations only
- TASK-FSRF-002: modifies write_outputs() and tests
- TASK-FSRF-003: modifies CLAUDE.md only
- TASK-FSRF-006: modifies README.md only

### Wave 2 (Parallel, 2 tasks)

Depend on TASK-FSRF-002 completing first (same module):
- TASK-FSRF-004: adds field to FeatureSpecResult
- TASK-FSRF-005: extends _read_input_files()
