---
id: TASK-OPS-BDDM-6
title: 'nats-core: add pytest-bdd to pyproject (advisory remediation)'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: medium
complexity: 1
task_type: bugfix
tags: [bdd, cross-repo-remediation, pytest-bdd]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 3
conductor_workspace: bdd-fix-wave3-natscore
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/nats-core
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: nats-core — add pytest-bdd to pyproject

## Description

Audit (2026-04-25) shows nats-core has **6 `.feature` files** but **zero `@task:` tags** and no `pytest-bdd` in `pyproject.toml`. Status: **advisory** — BDD scope authored, no current silent-bypass risk, but proactive remediation prevents future tagging from triggering the failure mode.

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `nats-core/pyproject.toml` test/dev dependencies.
- [ ] Reinstall.
- [ ] Verify `python -c "import pytest_bdd"` succeeds.
- [ ] Existing test suite still passes.
- [ ] Add comment referencing TASK-OPS-BDDM-6 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/nats-core/`

Direct mode. Match forge's pattern at `forge/pyproject.toml:34`. Isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
