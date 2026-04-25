---
id: TASK-OPS-BDDM-7
title: 'nats-infrastructure: add pytest-bdd to pyproject (proactive remediation)'
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
conductor_workspace: bdd-fix-wave3-natsinfra
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: nats-infrastructure — add pytest-bdd to pyproject

## Description

Audit (2026-04-25): nats-infrastructure has **0 `.feature` files** and no `pytest-bdd`. Status: **proactive** — added per user request as part of cross-repo remediation policy.

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `nats-infrastructure/pyproject.toml` test/dev dependencies.
- [ ] Reinstall.
- [ ] Verify `python -c "import pytest_bdd"` succeeds.
- [ ] Existing test suite still passes.
- [ ] Add comment referencing TASK-OPS-BDDM-7 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/`

Direct mode. Isolated to dev/test deps; no runtime impact.

**Note:** because nats-infrastructure has no current BDD scope, this is purely preventative — ensures future `/feature-spec` invocations land into a project that's already configured.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
