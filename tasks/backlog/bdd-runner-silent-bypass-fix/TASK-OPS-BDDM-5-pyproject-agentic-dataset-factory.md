---
id: TASK-OPS-BDDM-5
title: 'agentic-dataset-factory: add pytest-bdd to pyproject (advisory remediation)'
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
conductor_workspace: bdd-fix-wave3-adf
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: agentic-dataset-factory — add pytest-bdd to pyproject

## Description

Audit (2026-04-25) shows agentic-dataset-factory has **7 `.feature` files** but **zero `@task:` tags** and no `pytest-bdd` in `pyproject.toml`. Status: **advisory** — BDD scope authored, no current silent-bypass risk, but proactive remediation prevents future tagging from triggering the failure mode.

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `agentic-dataset-factory/pyproject.toml` test/dev dependencies.
- [ ] Reinstall (`pip install -e .[dev]` or equivalent for repo's tooling).
- [ ] Verify `python -c "import pytest_bdd; print(pytest_bdd.__version__)"` succeeds.
- [ ] Existing test suite still passes (no behavioural regression).
- [ ] Add a one-line comment in `pyproject.toml` next to the dep referencing TASK-OPS-BDDM-5 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/`

**Direct mode** — single-file edit. Match forge's pattern at `forge/pyproject.toml:34`.

**Risk:** isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7 (expanded by user request to cover all 8 Python repos in the workspace).
