---
id: TASK-OPS-BDDM-10
title: 'guardkit (self): add pytest-bdd to dev-deps for dogfooding'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: medium
complexity: 1
task_type: bugfix
tags: [bdd, cross-repo-remediation, pytest-bdd, dogfood]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 3
conductor_workspace: bdd-fix-wave3-guardkit-self
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/guardkit
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: guardkit (self) — add pytest-bdd to dev-deps for dogfooding

## Description

Audit (2026-04-25): GuardKit's own `pyproject.toml` has `pytest`, `pytest-cov`, `pytest-asyncio` but **no `pytest-bdd`**. GuardKit has 3 `.feature` files in `features/` with **zero `@task:` tags**, so it doesn't currently trigger the silent-bypass — but as the canonical implementation of the BDD oracle, GuardKit should dogfood the dependency it requires of all consumers.

This task also un-blocks the test infrastructure in case any developer adds `@task:` tags to GuardKit's own feature files (e.g., for self-tests of TASK-FIX-BDDM-1 / TASK-FIX-BDDM-2 in CI).

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `guardkit/pyproject.toml` test/dev dependencies (alongside `pytest>=7.4.3`, `pytest-cov>=4.1.0`, `pytest-asyncio>=0.23.0` at lines 59-61 / 68-70).
- [ ] Reinstall guardkit's own `.venv`.
- [ ] Verify `python -c "import pytest_bdd"` succeeds in guardkit's venv.
- [ ] Existing GuardKit test suite still passes.
- [ ] Add comment referencing TASK-OPS-BDDM-10 / FEAT-BDDM in pyproject.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/guardkit/` (this repo).

**Direct mode** — small two-line edit to pyproject.toml lines 59-61 + 68-70 (extras may differ; check the file's structure).

**Side-effect bonus:** the local `.venv` we use for `/task-review` analysis will then have `pytest_bdd` available, fixing the `ModuleNotFoundError: No module named 'pytest_bdd'` we hit during the regression-safety baseline check (review report §F).

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) §F — the GuardKit self-test currently relies on the silent-skip behaviour. After TASK-FIX-BDDM-1 ships, the **mocked** `has_pytest_bdd: False` tests still work (they monkeypatch the probe), so adding the real dep here is purely additive.
