---
id: TASK-OPS-BDDM-11
title: 'study-tutor: add pytest-bdd to pyproject (proactive remediation)'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: low
complexity: 1
task_type: bugfix
tags: [bdd, cross-repo-remediation, pytest-bdd]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 3
conductor_workspace: bdd-fix-wave3-studytutor
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/study-tutor
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: study-tutor — add pytest-bdd to pyproject

## Description

Audit (2026-04-25): study-tutor has **0 `.feature` files** and no `pytest-bdd`. Status: **proactive** — added per user request as part of cross-repo remediation policy. No current silent-bypass risk; pure preventative.

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `study-tutor/pyproject.toml` test/dev dependencies.
- [ ] Reinstall.
- [ ] Verify `python -c "import pytest_bdd"` succeeds.
- [ ] Existing test suite still passes.
- [ ] Add comment referencing TASK-OPS-BDDM-11 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/`

Direct mode. Isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
- Lowest priority of Wave 3 — no current BDD scope, no urgency. Useful only as future-proofing.
