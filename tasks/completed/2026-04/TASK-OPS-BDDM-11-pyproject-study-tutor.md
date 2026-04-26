---
id: TASK-OPS-BDDM-11
title: 'study-tutor: add pytest-bdd to pyproject (proactive remediation)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-26T00:00:00Z'
completed: '2026-04-26T00:00:00Z'
previous_state: in_review
state_transition_reason: 'All 5 ACs verified; pytest-bdd 8.1.0 installed in study-tutor, import succeeds, full test suite green (23 passed). study-tutor commit 2ba03ec.'
completed_location: 'tasks/completed/2026-04/TASK-OPS-BDDM-11-pyproject-study-tutor.md'
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
  status: passed
  coverage: null
  last_run: '2026-04-26T00:00:00Z'
  verification_artifact: '23 passed in 6.25s; pytest_bdd 8.1.0 import verified in study-tutor/.venv'
---

# Task: study-tutor — add pytest-bdd to pyproject

## Description

Audit (2026-04-25): study-tutor has **0 `.feature` files** and no `pytest-bdd`. Status: **proactive** — added per user request as part of cross-repo remediation policy. No current silent-bypass risk; pure preventative.

## Acceptance Criteria

- [x] Add `"pytest-bdd>=8.1,<9"` to `study-tutor/pyproject.toml` test/dev dependencies. — committed in study-tutor as `2ba03ec` (`chore(deps): add pytest-bdd>=8.1,<9 to dev group (TASK-OPS-BDDM-11)`).
- [x] Reinstall. — `.venv/bin/pip install -e ".[dev]"` installed `pytest-bdd-8.1.0` + `gherkin-official-29.0.0` + transitive deps (`parse`, `parse-type`, `Mako`, `MarkupSafe`).
- [x] Verify `python -c "import pytest_bdd"` succeeds. — `import pytest_bdd` resolves to `study-tutor/.venv/lib/python3.11/site-packages/pytest_bdd/__init__.py`; `importlib.metadata.version('pytest-bdd')` → `'8.1.0'`.
- [x] Existing test suite still passes. — `.venv/bin/pytest -q` → `23 passed in 6.25s`. No regressions.
- [x] Add comment referencing TASK-OPS-BDDM-11 / FEAT-BDDM. — 6-line comment block above the new pin in `pyproject.toml` dev group.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/`

Direct mode. Isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
- Lowest priority of Wave 3 — no current BDD scope, no urgency. Useful only as future-proofing.

## Verification (2026-04-26)

```bash
$ cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
$ .venv/bin/pip install -e ".[dev]"
# Successfully installed Mako-1.3.11 MarkupSafe-3.0.3 gherkin-official-29.0.0
#   parse-1.21.1 parse-type-0.6.6 pytest-bdd-8.1.0 study-tutor-0.1.0

$ .venv/bin/python -c "import pytest_bdd; from importlib.metadata import version; print(version('pytest-bdd'))"
# 8.1.0

$ .venv/bin/pytest -q
# 23 passed in 6.25s
```

Audit-confirmed pre-state: study-tutor had **0 `.feature` files** and `pytest_bdd`
was not importable (`ModuleNotFoundError: No module named 'pytest_bdd'`). This
remains a purely proactive add — the silent-bypass class-of-defect is closed
the moment the first `.feature` lands in study-tutor, regardless of whether
that lands tomorrow or in twelve months.

## Files Changed

**study-tutor** (committed as `2ba03ec`):
- `pyproject.toml` — added `"pytest-bdd>=8.1,<9"` to `[project.optional-dependencies].dev` with 6-line TASK-OPS-BDDM-11 / FEAT-BDDM comment block.

**guardkit** (this task file):
- Status `backlog` → `in_progress` → `in_review` → `completed`; ACs marked; verification recorded; archived to `tasks/completed/2026-04/`.
