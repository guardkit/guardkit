---
id: TASK-FAUD-003
title: Document the `guardkit feature audit` command
status: backlog
task_type: documentation
feature_id: FEAT-FAUD
wave: 3
implementation_mode: direct
complexity: 2
priority: low
created: 2026-06-16T00:00:00Z
depends_on: [TASK-FAUD-002]
tags: [feature-audit, docs]
---

# Task: Document `guardkit feature audit`

## Description

Document the new `guardkit feature audit` command (small, mechanical doc edit —
direct mode).

## Acceptance Criteria

- [ ] `CLAUDE.md` "Essential Commands" (or the Utilities section) lists
      `guardkit feature audit [--fix]` with a one-line description (detects stale
      feature-YAML statuses by comparing declared status to task locations;
      `--fix` reconciles them).
- [ ] The line states the exit-code contract (non-zero when stale features exist
      and `--fix` not passed) so it can be used as a CI guard.
- [ ] No code changes; documentation only.

## Implementation Notes

- Keep it to a single concise entry consistent with the surrounding command
  list; do not restructure the doc.
