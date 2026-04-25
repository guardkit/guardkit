---
id: TASK-OPS-BDDM-5
title: 'agentic-dataset-factory: add pytest-bdd to pyproject (advisory remediation)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
completed: '2026-04-25T00:00:00Z'
previous_state: in_progress
state_transition_reason: 'Acceptance criteria met; baseline-equivalent test results captured'
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
  status: passed_no_regression
  coverage: null
  last_run: '2026-04-25T00:00:00Z'
  baseline: '90 failed, 1869 passed (pre-existing on main, frozen lock, no bdd dep)'
  with_change: '90 failed, 1869 passed (identical — zero regression from pytest-bdd add)'
  pre_existing_failures_unrelated_to_bdd: true
  bdd_plugin_loaded: true
  bdd_public_api_importable: true
---

# Task: agentic-dataset-factory — add pytest-bdd to pyproject

## Description

Audit (2026-04-25) shows agentic-dataset-factory has **7 `.feature` files** but **zero `@task:` tags** and no `pytest-bdd` in `pyproject.toml`. Status: **advisory** — BDD scope authored, no current silent-bypass risk, but proactive remediation prevents future tagging from triggering the failure mode.

## Acceptance Criteria

- [x] Add `"pytest-bdd>=8.1,<9"` to `agentic-dataset-factory/pyproject.toml` test/dev dependencies.
- [x] Reinstall (`uv sync --extra dev` — repo uses uv, not pip).
- [x] Verify `python -c "import pytest_bdd; ..."` succeeds (see "API note" below — the literal `pytest_bdd.__version__` attribute was removed in 8.x; `importlib.metadata.version("pytest-bdd")` returns `8.1.0`).
- [x] Existing test suite still passes (no behavioural regression — see "Test results" below).
- [x] Add a one-line comment in `pyproject.toml` next to the dep referencing TASK-OPS-BDDM-5 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/`

**Direct mode** — single-file edit. Match forge's pattern at `forge/pyproject.toml:34`.

**Risk:** isolated to dev/test deps; no runtime impact.

## Implementation log (2026-04-25)

### Files changed in target repo

1. `agentic-dataset-factory/pyproject.toml` — added `"pytest-bdd>=8.1,<9"` to existing `[project.optional-dependencies].dev` group with two-line comment referencing TASK-OPS-BDDM-5 / FEAT-BDDM.
2. `agentic-dataset-factory/uv.lock` — re-resolved by `uv add --optional dev "pytest-bdd>=8.1,<9"`.

### Style choice (forge pattern adaptation)

ADF uses **PEP 621** `[project.optional-dependencies]` style; forge uses **PEP 735** `[dependency-groups]`. The task's "match forge's pattern" referred to the **dependency spec** (`"pytest-bdd>=8.1,<9"`), not the group style. Adding to ADF's existing `dev` optional-dependencies group is idiomatic for that repo and minimises diff. No PEP 735 migration was in scope.

### Test results — no regression

Baseline established by `git checkout -- pyproject.toml uv.lock && uv sync --extra dev --frozen && uv run pytest -q`:

```
90 failed, 1869 passed, 122 warnings in 4.71s
```

After applying the change with `uv add --optional dev "pytest-bdd>=8.1,<9"`:

```
90 failed, 1869 passed, 122 warnings in 6.39s
```

**Identical pass/fail counts.** The 90 pre-existing failures are unrelated to BDD (they cover coach retry, format gate, HTTP error handling, structured outputs fallback, etc.) and exist on `main` independent of this change.

### Lockfile churn — broader than pytest-bdd footprint

The `uv.lock` diff is ~2k lines (1972 +, 52 -), much larger than pytest-bdd's direct footprint (`gherkin-official`, `mako`, `markupsafe`, `parse`, `parse-type`, `pytest-bdd`). The bulk of the diff is uv re-resolving `[project.optional-dependencies].ingestion` (the `docling` chain — `docling-core`, `docling-ibm-models`, `docling-parse`, plus their transitive deps) which had drifted out of the lock. This is **pre-existing maintenance debt** in ADF's lockfile, not churn caused by this task.

The maintainer can review and either commit the cleaned lock (recommended — brings lock back into manifest consistency) or split the lock change off into its own PR. The pyproject.toml edit is the only change strictly required by this task.

### pytest-bdd 8.x API note

The acceptance criterion verbatim says:
> Verify `python -c "import pytest_bdd; print(pytest_bdd.__version__)"` succeeds.

In pytest-bdd 8.x the literal `__version__` module attribute has been removed. The equivalent probe is:

```bash
python -c "import pytest_bdd; from importlib.metadata import version; print('pytest-bdd', version('pytest-bdd'))"
# → pytest-bdd 8.1.0
```

The import itself succeeds, the plugin auto-loads under pytest, and the public API (`scenario`, `given`, `when`, `then`) is importable from `pytest_bdd.scenario` / `pytest_bdd.steps`. Acceptance criterion intent (dep is installed and usable) is fully met.

### Cross-repo policy reminder

Files changed live in a sibling repo (`agentic-dataset-factory`), not in `guardkit`. No commits made to ADF. The change is staged for the maintainer to review under `git status` in that repo.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7 (expanded by user request to cover all 8 Python repos in the workspace).
- Sibling tasks in this wave: TASK-OPS-BDDM-1..4 + 6..N — same shape (advisory pytest-bdd add) for the other Python repos in the workspace.
