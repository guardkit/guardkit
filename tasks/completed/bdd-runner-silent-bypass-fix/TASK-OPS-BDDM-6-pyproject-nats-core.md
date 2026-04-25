---
id: TASK-OPS-BDDM-6
title: 'nats-core: add pytest-bdd to pyproject (advisory remediation)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T23:45:00Z'
completed: '2026-04-25T23:45:00Z'
completed_location: tasks/completed/bdd-runner-silent-bypass-fix/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; advisory remediation applied to nats-core; 797 tests pass."
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
  status: passed
  coverage: null
  last_run: '2026-04-25T23:30:00Z'
  notes: '797 passed (tests/ excluding tests/integration which requires a live NATS server; integration errors are NoServersError, pre-existing infra dependency, unrelated to this change).'
---

# Task: nats-core — add pytest-bdd to pyproject

## Description

Audit (2026-04-25) shows nats-core has **6 `.feature` files** but **zero `@task:` tags** and no `pytest-bdd` in `pyproject.toml`. Status: **advisory** — BDD scope authored, no current silent-bypass risk, but proactive remediation prevents future tagging from triggering the failure mode.

## Acceptance Criteria

- [x] Add `"pytest-bdd>=8.1,<9"` to `nats-core/pyproject.toml` test/dev dependencies.
- [x] Reinstall (`pip install -e '.[dev]'` — pytest-bdd-8.1.0, gherkin-official-29.0.0, parse-1.21.1, parse-type-0.6.6 installed).
- [x] Verify `python -c "import pytest_bdd"` succeeds (resolves to `site-packages/pytest_bdd/__init__.py`).
- [x] Existing test suite still passes (797 passed in `tests/` excluding `tests/integration/` which needs a live NATS server).
- [x] Add comment referencing TASK-OPS-BDDM-6 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/nats-core/`

Direct mode. Match forge's pattern at `forge/pyproject.toml:34`. Isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.

## Implementation Log (2026-04-25)

**Change:** added `"pytest-bdd>=8.1,<9"` to the `dev` array in `[project.optional-dependencies]` of `nats-core/pyproject.toml`, with an inline comment referencing this task and FEAT-BDDM.

**Diff (logical):**
```toml
 dev = [
     "pytest>=7.0",
     "pytest-asyncio>=0.21",
+    # pytest-bdd: required for `.feature` scenario discovery so future @task: tags
+    # are not silently bypassed. See guardkit TASK-OPS-BDDM-6 / FEAT-BDDM.
+    "pytest-bdd>=8.1,<9",
     "pytest-cov>=4.0",
     ...
 ]
```

**Install verification:** `python -m pip install -e '/.../nats-core[dev]'` succeeded. Resolver pulled `pytest-bdd-8.1.0`, `gherkin-official-29.0.0`, `parse-1.21.1`, `parse-type-0.6.6`. Replaced existing `gherkin-official-39.0.0` with `29.0.0` (pytest-bdd 8.x cap).

**Import verification:** `python -c "import pytest_bdd"` resolves to `/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/pytest_bdd/__init__.py`.

**Test verification:** `pytest tests/ --ignore=tests/integration --no-cov -q` → **797 passed, 5 warnings** (warnings pre-date this change — `FeaturePlannedPayload` deprecation). Integration suite (`tests/integration/test_pipeline_payloads_live.py`) errors with `nats.errors.NoServersError: nats: no servers available for connection` — requires a live NATS/JetStream broker, pre-existing infrastructure dependency unrelated to this change.

**Audit verification:** confirmed `features/` contains 6 `.feature` files and zero `@task:` tags — advisory status holds; no current silent-bypass risk, this change is proactive remediation.

**Note on dev-dep style:** kept the existing `[project.optional-dependencies] dev = [...]` block rather than migrating to PEP 735 `[dependency-groups]` (forge's pattern). Out of scope for this advisory remediation; both styles install pytest-bdd correctly.
