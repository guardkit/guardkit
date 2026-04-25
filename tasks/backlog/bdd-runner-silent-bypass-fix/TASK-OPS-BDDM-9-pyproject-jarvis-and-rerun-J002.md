---
id: TASK-OPS-BDDM-9
title: 'jarvis: add pytest-bdd to pyproject + re-run FEAT-J002 with active BDD verification'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: high
complexity: 4
task_type: bugfix
tags: [bdd, jarvis, cross-repo-remediation, pytest-bdd, critical]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: task-work
wave: 3
conductor_workspace: bdd-fix-wave3-jarvis
depends_on: [TASK-FIX-BDDM-1, TASK-FIX-BDDM-2]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/jarvis
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: jarvis — add pytest-bdd + re-run FEAT-J002 (CRITICAL)

## Description

**This is the highest-priority Wave 3 task** because jarvis is the only repo audited (2026-04-25) with currently-silent-bypassed BDD verification: **86 `@task:` tags across 3 feature files** for FEAT-J002 / FEAT-J003, with zero pytest-bdd in [pyproject.toml](/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml).

Empirical evidence:
- `jarvis/docs/history/autobuild-FEAT-J002-history.md` — 10 occurrences of "pytest-bdd not importable".
- `jarvis/docs/history/autobuild-FEAT-J003-history-cancelled.md` — 11 occurrences.
- jarvis `pyproject.toml` lines 76-78: `pytest, pytest-asyncio, pytest-cov` (no pytest-bdd).

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to jarvis `pyproject.toml` test/dev dependencies (matching forge's declaration at `forge/pyproject.toml:34`).
- [ ] Reinstall the jarvis dev environment (`pip install -e .[dev]` or `uv sync`, depending on jarvis's tooling).
- [ ] Verify `python -c "import pytest_bdd; print(pytest_bdd.__version__)"` succeeds in jarvis's worktree env.
- [ ] **Re-run AutoBuild on a representative FEAT-J002 task** (pick one with the most tagged scenarios — e.g., TASK-J002-008 has 5+ in the feature file) using the GuardKit fix from TASK-FIX-BDDM-1 in place.
- [ ] Confirm the resulting `task_work_results.json` now includes a non-vacuous `bdd_results` block with `scenarios_passed`, `scenarios_failed`, or `scenarios_pending` reflecting the actual scenario outcomes.
- [ ] If scenarios fail (real assertion failures) or pend (step-defs not yet implemented) → file follow-up tasks in jarvis's own `tasks/backlog/` for the implementation gaps. **Do NOT remediate scenario logic as part of this task** — its scope is config + verification of the fix.
- [ ] **FEAT-J003 is cancelled** (history filename suffix `-cancelled.md`); document the BDD-verification gap as a known retrospective limitation in jarvis's notes/changelog. Do not re-run.
- [ ] Add a one-line entry to jarvis's `pyproject.toml` comment block (or CHANGELOG, depending on jarvis convention) explaining the dependency was added per TASK-OPS-BDDM-9 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/jarvis/`

**Pre-requisite:** TASK-FIX-BDDM-1 must be merged to GuardKit `main` AND jarvis's installed GuardKit version must be updated to include the fix. Otherwise the silent-bypass would continue masking any real BDD failures during the re-run.

**Workflow:**
1. cd to jarvis worktree.
2. Edit `pyproject.toml`. Match forge's pattern. Likely location: in the `[project.optional-dependencies] test` or `[dependency-groups] dev` table — depends on jarvis's setup.
3. Reinstall.
4. Verify import.
5. Pick TASK-J002-008 (or similar) — confirm it's still in jarvis backlog.
6. Run `guardkit autobuild task TASK-J002-008` (or whatever jarvis's invocation is).
7. Inspect `.guardkit/worktrees/.../task_work_results.json` for `bdd_results` key.
8. Document outcome.

**Risk if TASK-FIX-BDDM-1 not yet merged:** the re-run would still silent-bypass. Block this task on Wave 1 GuardKit core fix (already encoded in `depends_on`).

**Risk on jarvis pyproject change:** isolated, well-bounded — adding a dev dependency cannot break runtime jarvis behaviour, only test execution. Verify jarvis's own test suite still passes after the dep is added.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) §F.7 + recommendation R7 for context.
- jarvis is in scope because it's the canonical example of the defect this whole feature addresses.
