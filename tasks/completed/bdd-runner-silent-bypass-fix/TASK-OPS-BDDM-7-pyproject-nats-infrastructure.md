---
id: TASK-OPS-BDDM-7
title: 'nats-infrastructure: add pytest-bdd to pyproject (proactive remediation)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T23:55:00Z'
completed: '2026-04-25T23:55:00Z'
completed_location: tasks/completed/bdd-runner-silent-bypass-fix/
previous_state: in_progress
state_transition_reason: 'All acceptance criteria met; preventative pytest-bdd declaration added via PEP 735 dependency-groups; 685 tests pass.'
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
  status: passed
  coverage: null
  last_run: '2026-04-25T23:55:00Z'
  notes: '685 passed, 6 skipped, 32 deselected (integration tests requiring live NATS server). pytest-bdd-8.1.0 plugin loaded by pytest.'
---

# Task: nats-infrastructure — add pytest-bdd to pyproject

## Description

Audit (2026-04-25): nats-infrastructure has **0 `.feature` files** and no `pytest-bdd`. Status: **proactive** — added per user request as part of cross-repo remediation policy.

## Acceptance Criteria

- [x] Add `"pytest-bdd>=8.1,<9"` to `nats-infrastructure/pyproject.toml` test/dev dependencies.
- [x] Reinstall (`python -m pip install --group dev` from target dir, exit 0).
- [x] Verify `python -c "import pytest_bdd"` succeeds (resolves to `site-packages/pytest_bdd/__init__.py`, version 8.1.0).
- [x] Existing test suite still passes (685 passed, 6 skipped, 32 deselected — same outcome as baseline; integration tests deselected by default `-m 'not integration'`).
- [x] Add comment referencing TASK-OPS-BDDM-7 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/`

Direct mode. Isolated to dev/test deps; no runtime impact.

**Note:** because nats-infrastructure has no current BDD scope, this is purely preventative — ensures future `/feature-spec` invocations land into a project that's already configured.

## Implementation Log (2026-04-25)

### Style choice — PEP 735 over PEP 621 optional-dependencies

Sister tasks BDDM-5 (ADF) and BDDM-6 (nats-core) added pytest-bdd to an existing `[project.optional-dependencies] dev` block. **nats-infrastructure has no `[project]` table at all** — its `pyproject.toml` was a 10-line file containing only `[tool.pytest.ini_options]`. The repo is a Docker/JetStream infrastructure deployment, not a Python package.

Two viable paths:

1. **Add a stub `[project]` block** with invented `name`/`version` to host `[project.optional-dependencies] dev` (matches sibling-task pattern textually, but mis-declares the repo as a Python package).
2. **Add PEP 735 `[dependency-groups]`** (matches forge's pattern, declares dev deps without forcing project metadata, lightest-touch).

Chose **option 2**. Rationale:
- The repo is genuinely not a Python package — adding `[project]` would be misleading to anyone reading the file.
- PEP 735 was designed for exactly this case (declaring dev deps without claiming the directory is a buildable package).
- Forge already uses this pattern in the workspace, so it's a known idiom locally.
- Local pip is 26.0.1 (PEP 735 `--group` install supported since 25.1).

This deviates textually from the BDDM-5/6 pattern but follows the same spirit (declare dev dep + comment + reinstall + verify). BDDM-6's note explicitly said dev-dep style choice is out of scope of advisory remediation.

### Files changed in target repo

`nats-infrastructure/pyproject.toml` — added `[dependency-groups] dev = ["pytest-bdd>=8.1,<9"]` block with explanatory comment. No other files changed (no lockfile in this repo).

**Diff (logical):**
```toml
 [tool.pytest.ini_options]
 ...

+# PEP 735 dev-dependency group. nats-infrastructure is a Docker/infra repo
+# (no [project] table) — this is the lightest-touch way to declare test deps.
+# Install with: python -m pip install --group dev
+[dependency-groups]
+dev = [
+    # pytest-bdd: required for `.feature` scenario discovery so future @task: tags
+    # are not silently bypassed. See guardkit TASK-OPS-BDDM-7 / FEAT-BDDM.
+    "pytest-bdd>=8.1,<9",
+]
```

### Install verification

`python -m pip install --group dev` (run from `nats-infrastructure/`) succeeded with exit 0. pytest-bdd-8.1.0 was already present in the system Python (`/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/pytest_bdd/`) from BDDM-5/6 sibling-task installs — pip confirmed the requirement and made no changes.

### Import verification

`python -c "import pytest_bdd; from importlib.metadata import version; print('pytest-bdd', version('pytest-bdd'), '@', pytest_bdd.__file__)"`
→ `pytest-bdd 8.1.0 @ /.../site-packages/pytest_bdd/__init__.py`

### Plugin-load verification

`python -m pytest -V` from `nats-infrastructure/` confirms pytest auto-loads the plugin:
```
plugins: anyio-4.12.0, timeout-2.4.0, asyncio-1.3.0, langsmith-0.7.22, bdd-8.1.0, Faker-40.11.1, cov-7.0.0
```

### Test verification

`python -m pytest -q` (pyproject.toml addopts: `-m 'not integration'`):
```
685 passed, 6 skipped, 32 deselected in 1.00s
```

The 32 deselected are integration tests requiring a live NATS server (`-m integration` opt-in). The 6 skipped are KV-watch + provisioning conditional skips (pre-existing). Zero regressions from the dev-group addition.

### Audit verification

Confirmed the repo still has 0 `.feature` files (`find ... -name "*.feature"` returns nothing) — proactive status holds; this change is purely preventative remediation per cross-repo policy.

### Cross-repo policy reminder

Files changed live in a sibling repo (`nats-infrastructure`), not in `guardkit`. **No commits made to nats-infrastructure** — change is left in working tree for the maintainer (the user) to review under `git status` in that repo.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
- Sibling tasks: TASK-OPS-BDDM-5 (ADF), TASK-OPS-BDDM-6 (nats-core) — same shape, different repos. This one differs in style (PEP 735 vs PEP 621) because the target repo has no `[project]` block; both styles install pytest-bdd correctly.
