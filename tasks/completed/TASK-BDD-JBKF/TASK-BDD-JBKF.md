---
id: TASK-BDD-JBKF
title: Backfill R2 activation on jarvis by tagging scenarios and running pytest-bdd
status: completed
task_type: verification
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
completed: 2026-04-22T00:00:00Z
completed_location: tasks/completed/TASK-BDD-JBKF/
previous_state: in_review
state_transition_reason: "Verification complete; outcome recorded (Outcome D); P0 defect TASK-FIX-F584 filed and blocks TASK-COH-RUN1"
priority: high
complexity: 3
tags: [autobuild, r2, bdd-oracle, backfill, jarvis, task-bdd-e8954, verification]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 1
conductor_workspace: r2-pipeline-closure-wave1-r2-backfill
depends_on: []
outcome: "Outcome D (P0 defect in R2) — silent false approval on pytest usage errors"
evidence: .claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md
defect_filed: TASK-FIX-F584
organized_files:
  - TASK-BDD-JBKF.md
---

# Task: Backfill R2 activation on jarvis by tagging scenarios and running pytest-bdd

## Problem Statement

FEAT-JARVIS-001 had a well-formed `features/project-scaffolding-supervisor-sessions.feature` with 15+ scenarios, but zero `@task:J001-*` tags — so R2 (BDD oracle, TASK-BDD-E8954) never fired. R2's runner has never been exercised against real cohort code. Until it has, we don't know whether the wiring actually works end-to-end on a non-fixture feature.

This task retroactively activates R2 on the completed jarvis codebase: tag two of the existing scenarios with `@task:TASK-J001-*`, run `pytest-bdd` against the merged code, and confirm the three-state breakdown (passed / failed / pending) behaves correctly — most importantly that pending does **not** collapse into failed.

## Scope (REVISED 2026-04-22 after premise check)

### In-Scope

- Choose 2 jarvis scenarios in `features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature`. Map each to an existing J001 task ID (TASK-J001-001, -006, -007, or -008 — all present in `.guardkit/autobuild/`).
- Add `@task:TASK-J001-XXX` tags above the chosen `Scenario:` lines (working copy only, not committed).
- Create a **throwaway venv** in jarvis (`.venv-r2-probe/`, outside `pyproject.toml`) with `pytest` and `pytest-bdd` installed.
- Invoke `guardkit.orchestrator.quality_gates.bdd_runner.run_bdd_for_task(task_id, jarvis_path, python_executable=<throwaway_venv_python>)` for each tagged task ID.
- Observe which of **three** outcomes occurs (see Expected Outcomes) and record it.
- Document the activation path, the outcome category, raw runner output, and interpretation in `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md`.

### Out-of-Scope

- Writing step definitions for any scenario — this task intentionally exercises the no-step-defs path.
- Adding `pytest-bdd` to jarvis's `pyproject.toml` — the throwaway venv keeps the change environmental, not source.
- Re-running the full FEAT-JARVIS-001 autobuild.
- Landing the `@task:` tags in jarvis's main branch.
- **Verifying the `scenarios_passed` path end-to-end** — see below. That verification is delegated to TASK-COH-RUN1 (forge/study-tutor cohort), which will have real step defs by construction.

### Why pass-state verification is delegated

The original AC assumed jarvis had pytest-bdd glue that could exercise the implementation code. It does not — no `step_defs/` dir, no `scenarios(...)` calls, and `pytest-bdd` is absent from `pyproject.toml` (verified 2026-04-22). Writing glue just to produce a passed scenario would inflate scope well beyond a throwaway evidence exercise. The pass-detection path is well-established pytest-bdd library behaviour — it isn't novel GuardKit code — and forge/study-tutor will exercise it naturally. TASK-COH-RUN1 picks up the passed-state confirmation.

## Acceptance Criteria (REVISED)

- [ ] Two scenarios in the jarvis `.feature` file have `@task:TASK-J001-XXX` tags added (working copy, not committed to jarvis main).
- [ ] A throwaway venv `.venv-r2-probe/` exists in the jarvis checkout with `pytest-bdd` installed (not added to `pyproject.toml`).
- [ ] `bdd_runner.run_bdd_for_task(...)` was invoked for each tagged task ID using the throwaway venv's python.
- [ ] **Primary AC (three-state model):** outcome is one of the three enumerated below, and the outcome category is recorded explicitly in the evidence report:
  - **Outcome A (desired):** `BDDResult is not None`, `scenarios_pending > 0`, `scenarios_failed == 0`. Three-state model works — pending classified as pending.
  - **Outcome B (P0 defect in R2):** `BDDResult is not None`, `scenarios_failed > 0`. Pending collapsed into failed. File defect against TASK-BDD-E8954, halt cohort.
  - **Outcome C (separate defect in R2):** Runner returns `None` via the third silent-skip path (`bdd_runner.py:430-441`, triggered when `pytest` exit code is 5 and no passed/failed/pending parsed). Undefined-steps feature looked like "no tests collected" rather than all-pending. File separate defect against TASK-BDD-E8954 — distinct from Outcome B.
- [ ] Evidence written to `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md` containing: diff of tags added, venv creation commands, runner invocation command, raw stdout/stderr, parsed `BDDResult` (or the `None` return + exit code if Outcome C), the outcome category (A/B/C), and interpretation.
- [ ] **If Outcome B or C:** a P0 defect task is filed against TASK-BDD-E8954 before TASK-COH-RUN1 starts, and COH-RUN1's R2 pre-flight is marked as a hard block on the defect fix.
- [ ] Jarvis working copy is reverted (tags removed, venv directory added to a local `.gitignore` entry or deleted) before task close.

## Implementation Notes

- **Do not commit the tags or the venv to jarvis main.** This is evidence-gathering for GuardKit, not a jarvis change.
- **Three silent-skip paths in `bdd_runner.run_bdd_for_task`** (all return `None`):
  1. No `.feature` file contains the `@task:TASK-ID` tag (`bdd_runner.py:394-400`).
  2. `pytest_bdd` not importable in the target environment (`bdd_runner.py:402-409`).
  3. pytest collected zero tests — `passed == 0 and not failures and not pending and returncode == 5` (`bdd_runner.py:430-441`).
  Path (3) was not contemplated in the original AC. A tagged feature with no step defs is the exact scenario where path (3) could fire in place of the expected "all-pending" outcome. Distinguishing (3) from "three-state works" is the new load-bearing assertion this task makes.
- **The task tag format** is `@task:<full-task-id>`, produced by `task_tag()`: e.g., `@task:TASK-J001-001`. The pytest marker derived from this tag via `_build_pytest_argv` is `task_TASK_J001_001` (colons and hyphens replaced with underscores).
- Pass-state ("scenario passes against current code") is delegated to TASK-COH-RUN1 — see Scope rationale above.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§R2 per-remediation, §Addendum A)
- R2 task: `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md`
- Jarvis feature file (actual path): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature`
- Jarvis autobuild state (task IDs to tag with): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/` — TASK-J001-001, -006, -007, -008 directories exist.
- Downstream: TASK-COH-RUN1 (pass-state verification lives there).
- Graphiti node: *"BDD oracle must not collapse pending into failed"*

## Revision Log

- **2026-04-22 (AC re-scope):** Dropped original AC #3 (`scenarios_passed >= 1`) after confirming jarvis has no pytest-bdd glue and no step defs. Added explicit three-outcome AC covering the third silent-skip path at `bdd_runner.py:430-441`. Pass-state verification delegated to TASK-COH-RUN1. Authorised throwaway venv (`.venv-r2-probe/`) in jarvis working copy.
